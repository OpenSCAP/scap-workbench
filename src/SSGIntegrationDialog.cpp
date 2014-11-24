/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
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

#include "SSGIntegrationDialog.h"
#include "Utils.h"

#include <QDir>

SSGIntegrationDialog::SSGIntegrationDialog(QWidget* parent):
    QDialog(parent)
{
    mUI.setupUi(this);
    mUI.ssgLogo->setPixmap(getSharePixmap("ssg_logo.png"));

    scrapeSSGVariants();

    QObject::connect(
        mUI.openCustomContent, SIGNAL(released()),
        this, SLOT(reject())
    );
}

SSGIntegrationDialog::~SSGIntegrationDialog()
{}

const QString& SSGIntegrationDialog::getSelectedSSGFile() const
{
    return mSelectedSSGFile;
}

bool SSGIntegrationDialog::isSSGAvailable()
{
    return true;
}

void SSGIntegrationDialog::variantRequested()
{
    QObject* sender = QObject::sender();
    QPushButton* button = dynamic_cast<QPushButton*>(sender);

    if (!button)
        return;

    const QString variant = button->text();

    QDir dir(SCAP_WORKBENCH_SSG_DIRECTORY);
    dir.cd(variant);

    mSelectedSSGFile = dir.absoluteFilePath(QString("ssg-%1-ds.xml").arg(variant));
    accept();
}

void SSGIntegrationDialog::scrapeSSGVariants()
{
    const QDir dir(SCAP_WORKBENCH_SSG_DIRECTORY);
    const QStringList variants = dir.entryList(QDir::Dirs | QDir::NoDotAndDotDot);

    for (QStringList::const_iterator it = variants.constBegin();
         it != variants.constEnd(); ++it)
    {
        QPushButton* button = new QPushButton(*it, mUI.variants);
        mUI.variants->layout()->addWidget(button);

        QObject::connect(
            button, SIGNAL(released()),
            this, SLOT(variantRequested())
        );
    }
}
