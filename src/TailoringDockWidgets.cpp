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

#include "TailoringDockWidgets.h"
#include "TailoringWindow.h"
#include "APIHelpers.h"

ProfilePropertiesDockWidget::ProfilePropertiesDockWidget(TailoringWindow* window, QWidget* parent):
    QDockWidget(parent),

    mRefreshInProgress(false),
    mWindow(window)
{
    mUI.setupUi(this);

    QObject::connect(
        mUI.title, SIGNAL(textChanged(QString)),
        this, SLOT(profileTitleChanged(QString))
    );

    QObject::connect(
        mUI.description, SIGNAL(textChanged()),
        this, SLOT(profileDescriptionChanged())
    );
}

ProfilePropertiesDockWidget::~ProfilePropertiesDockWidget()
{}

void ProfilePropertiesDockWidget::refresh()
{
    if (mUI.id->text() != mWindow->getProfileID())
        mUI.id->setText(mWindow->getProfileID());

    if (mUI.title->text() != mWindow->getProfileTitle())
    {
        // This prevents a new undo command being spawned as a result of refreshing
        mRefreshInProgress = true;
        mUI.title->setText(mWindow->getProfileTitle());
        mRefreshInProgress = false;
    }

    if (mUI.description->toPlainText() != mWindow->getProfileDescription())
    {
        // This prevents a new undo command being spawned as a result of refreshing
        mRefreshInProgress = true;
        mUI.description->setPlainText(mWindow->getProfileDescription());
        mRefreshInProgress = false;
    }
}

void ProfilePropertiesDockWidget::profileTitleChanged(const QString& newTitle)
{
    if (mRefreshInProgress)
        return;

    mWindow->setProfileTitleWithUndoCommand(newTitle);
}

void ProfilePropertiesDockWidget::profileDescriptionChanged()
{
    if (mRefreshInProgress)
        return;

    mWindow->setProfileDescriptionWithUndoCommand(mUI.description->toPlainText());
}

XCCDFItemPropertiesDockWidget::XCCDFItemPropertiesDockWidget(TailoringWindow* window, QWidget* parent):
    QDockWidget(parent),

    mXccdfItem(0),
    mXccdfPolicy(0),

    mRefreshInProgress(false),

    mWindow(window)
{
    mUI.setupUi(this);

    QObject::connect(
        mUI.valueComboBox, SIGNAL(editTextChanged(QString)),
        this, SLOT(valueChanged(QString))
    );
}

XCCDFItemPropertiesDockWidget::~XCCDFItemPropertiesDockWidget()
{}

void XCCDFItemPropertiesDockWidget::setXccdfItem(struct xccdf_item* item, struct xccdf_policy* policy)
{
    mXccdfItem = item;
    mXccdfPolicy = policy;

    refresh();
}

void XCCDFItemPropertiesDockWidget::refresh()
{
    if (mRefreshInProgress)
        return;

    if (mXccdfItem && xccdf_item_get_type(mXccdfItem) == XCCDF_VALUE)
    {
        struct xccdf_value* value = xccdf_item_to_value(mXccdfItem);

        if (mUI.idLineEdit->text() == xccdf_value_get_id(value) &&
            mUI.valueComboBox->currentText() == mWindow->getCurrentValueValue(value))
        {
            // no need to refresh, user is currently editing
            // refreshing would lose focus of the combobox, which makes editing hard to use
            return;
        }
    }

    mRefreshInProgress = true;

    mUI.titleLineEdit->setText(QObject::tr("<no item selected>"));
    mUI.idLineEdit->setText("");
    mUI.typeLineEdit->setText("");
    mUI.descriptionBrowser->setHtml("");
    mUI.identsBrowser->setHtml("");

    mUI.identsLabel->hide();
    mUI.identsBrowser->hide();

    mUI.valueGroupBox->hide();
    mUI.valueComboBox->clear();
    mUI.valueComboBox->setEditText("");
    mUI.valueComboBox->lineEdit()->setValidator(0);

    if (mXccdfItem)
    {
        mUI.titleLineEdit->setText(mWindow->getXCCDFItemTitle(mXccdfItem));
        mUI.idLineEdit->setText(QString::fromUtf8(xccdf_item_get_id(mXccdfItem)));
        switch (xccdf_item_get_type(mXccdfItem))
        {
            case XCCDF_BENCHMARK:
                mUI.typeLineEdit->setText(QObject::tr("xccdf:Benchmark"));
                break;
            case XCCDF_GROUP:
                mUI.typeLineEdit->setText(QObject::tr("xccdf:Group"));
                break;
            case XCCDF_RULE:
                mUI.typeLineEdit->setText(QObject::tr("xccdf:Rule"));
                break;
            case XCCDF_VALUE:
                mUI.typeLineEdit->setText(QObject::tr("xccdf:Value"));
                break;

            default:
                break;
        }
        mUI.descriptionBrowser->setHtml(mWindow->getXCCDFItemDescription(mXccdfItem));

        if (xccdf_item_get_type(mXccdfItem) == XCCDF_VALUE)
        {
            struct xccdf_value* value = xccdf_item_to_value(mXccdfItem);
            xccdf_value_type_t valueType = xccdf_value_get_type(value);

            switch (valueType)
            {
                case XCCDF_TYPE_NUMBER:
                    // XCCDF specification says:
                    // if element’s @type attribute is “number”, then a tool might choose
                    // to reject user tailoring input that is not composed of digits.
                    //
                    // This implies integers and not decimals.
                    mUI.valueComboBox->lineEdit()->setValidator(new QIntValidator(this));
                    mUI.valueTypeLabel->setText(QObject::tr("(number)"));
                    break;
                case XCCDF_TYPE_STRING:
                    mUI.valueComboBox->lineEdit()->setValidator(0);
                    mUI.valueTypeLabel->setText(QObject::tr("(string)"));
                    break;
                case XCCDF_TYPE_BOOLEAN:
                    // This is my best effort since the specification doesn't say what should be allowed.
                    const QRegExp regex("true|false|True|False|TRUE|FALSE|1|0|yes|no|Yes|No|YES|NO");
                    mUI.valueComboBox->lineEdit()->setValidator(new QRegExpValidator(regex, this));
                    mUI.valueTypeLabel->setText(QObject::tr("(bool)"));
                    break;
            }

            struct xccdf_value_instance_iterator* it = xccdf_value_get_instances(value);
            while (xccdf_value_instance_iterator_has_more(it))
            {
                struct xccdf_value_instance* instance = xccdf_value_instance_iterator_next(it);
                mUI.valueComboBox->addItem(QString::fromUtf8(xccdf_value_instance_get_value(instance)));
            }
            xccdf_value_instance_iterator_free(it);

            mUI.valueComboBox->setEditText(mWindow->getCurrentValueValue(value));

            mUI.valueComboBox->insertSeparator(1);
            mUI.valueGroupBox->show();
        }
        else if (xccdf_item_get_type(mXccdfItem) == XCCDF_RULE)
        {
            bool empty = true;

            QString html = "";
            struct xccdf_ident_iterator* idents = xccdf_rule_get_idents(xccdf_item_to_rule(mXccdfItem));
            while (xccdf_ident_iterator_has_more(idents))
            {
                empty = false;

                struct xccdf_ident* ident = xccdf_ident_iterator_next(idents);
                html += QString("[<i>%1</i>] - <b>%2</b><br />").arg(
                    QString::fromUtf8(xccdf_ident_get_system(ident)),
                    QString::fromUtf8(xccdf_ident_get_id(ident))
                );

            }
            xccdf_ident_iterator_free(idents);

            if (!empty)
            {
                mUI.identsBrowser->setHtml(html);

                mUI.identsLabel->show();
                mUI.identsBrowser->show();
            }
        }
    }

    mRefreshInProgress = false;
}

void XCCDFItemPropertiesDockWidget::valueChanged(const QString& newValue)
{
    if (mRefreshInProgress)
        return;

    mWindow->setValueValueWithUndoCommand(xccdf_item_to_value(mXccdfItem), newValue);
    // For the unlikely case of description or title having a <sub> element dependent
    // on the value we just changed.
    refresh();
}
