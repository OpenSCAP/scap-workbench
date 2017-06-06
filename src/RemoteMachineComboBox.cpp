/*
 * Copyright 2014 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "RemoteMachineComboBox.h"
#include "OscapScannerRemoteSsh.h"

RemoteMachineComboBox::RemoteMachineComboBox(QWidget* parent):
    QWidget(parent)
{
    mUI.setupUi(this);
    setFocusProxy(mUI.host);

#if (QT_VERSION >= QT_VERSION_CHECK(4, 7, 0))
    // placeholder text is only supported in Qt 4.7 onwards
    mUI.host->setPlaceholderText(QObject::tr("username@hostname"));
#endif

    mQSettings = new QSettings(this);

    mRecentComboBox = mUI.recentComboBox;
    QObject::connect(
        mRecentComboBox, SIGNAL(currentIndexChanged(int)),
        this, SLOT(updateHostPort(int))
    );

    setRecentMachineCount(5);
    syncFromQSettings();

}

RemoteMachineComboBox::~RemoteMachineComboBox()
{
    delete mQSettings;
}

QString RemoteMachineComboBox::getTarget() const
{
    return QString("%1:%2").arg(mUI.host->text()).arg(mUI.port->value());
}

void RemoteMachineComboBox::setRecentMachineCount(unsigned int count)
{
    while (static_cast<unsigned int>(mRecentTargets.size()) > count)
        mRecentTargets.removeLast();

    while (static_cast<unsigned int>(mRecentTargets.size()) < count)
        mRecentTargets.append("");
}

unsigned int RemoteMachineComboBox::getRecentMachineCount() const
{
    return mRecentTargets.size();
}

void RemoteMachineComboBox::notifyTargetUsed(const QString& target)
{
    QString host;
    short port;
    OscapScannerRemoteSsh::splitTarget(target, host, port);

    // skip invalid suggestions
    if (host.isEmpty() || port == 0)
        return;

    const unsigned int machineCount = getRecentMachineCount();

    // this moves target to the beginning of the list if it was in the list already
    mRecentTargets.prepend(target);
    mRecentTargets.removeDuplicates();

    setRecentMachineCount(machineCount);

    syncToQSettings();
    syncRecentMenu();

    // we can be sure there is at least 2 itens in ComboBox, "Recent" and the last entered host
    mRecentComboBox->setCurrentIndex(1);
}

void RemoteMachineComboBox::clearHistory()
{
    mUI.host->setText("");
    mUI.port->setValue(22);

    const unsigned int machineCount = getRecentMachineCount();
    mRecentTargets.clear();
    setRecentMachineCount(machineCount);

    syncToQSettings();
    syncRecentMenu();
}

void RemoteMachineComboBox::syncFromQSettings()
{
    QVariant value = mQSettings->value("recent-remote-machines");
    QStringList list = value.toStringList();

    const unsigned int machineCount = getRecentMachineCount();
    mRecentTargets = list;
    setRecentMachineCount(machineCount);
    syncRecentMenu();
}

void RemoteMachineComboBox::syncToQSettings()
{
    mQSettings->setValue("recent-remote-machines", QVariant(mRecentTargets));
}

void RemoteMachineComboBox::syncRecentMenu()
{
    mRecentComboBox->clear();

    mRecentComboBox->addItem(QString("Recent"));

    bool empty = true;
    for (QStringList::iterator it = mRecentTargets.begin(); it != mRecentTargets.end(); ++it)
    {
        if (it->isEmpty())
            continue;

        mRecentComboBox->addItem(*it, QVariant(*it));

        empty = false;
    }

    if (!empty)
    {
        mRecentComboBox->insertSeparator(mRecentComboBox->count());
        QString clear = QString("Clear History");
        mRecentComboBox->addItem(clear, QVariant(clear));
    }

    mRecentComboBox->setEnabled(!empty);
}

void RemoteMachineComboBox::updateHostPort(int index)
{
    const QVariant data = mRecentComboBox->itemData(index);
    const QString& target = data.toString();

    if (target.isEmpty())
    {
        mUI.host->setText("");
        mUI.port->setValue(22);
        return;
    }

    if (!target.compare("Clear History"))
    {
        clearHistory();
        return;
    }


    QString host;
    short port;

    OscapScannerRemoteSsh::splitTarget(target, host, port);

    mUI.host->setText(host);
    mUI.port->setValue(port);

}
